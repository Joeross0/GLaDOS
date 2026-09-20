"""QLoRA fine-tune from local script dumps.

Ollama cannot train weights. This trains a LoRA on the matching Hugging Face
Dolphin Llama 3 8B, then can serve it on an OpenAI-compatible port.
Needs an NVIDIA GPU with ~8 GB free. Close the TUI and Ollama first.
"""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from .style_model import collect_source_files, extract_pairs

OUTPUT_DIR = Path("data/finetune")
DATASET_PATH = OUTPUT_DIR / "train.jsonl"
ADAPTER_DIR = OUTPUT_DIR / "adapter"
BASE_MODEL = "cognitivecomputations/dolphin-2.9-llama3-8b"
DEFAULT_PORT = 11435


def write_dataset() -> tuple[Path, int]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs: list[dict[str, list[dict[str, str]]]] = []
    seen: set[str] = set()
    for path in collect_source_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pair in extract_pairs(text):
            assistant = pair["messages"][-1]["content"]
            if assistant in seen:
                continue
            seen.add(assistant)
            pairs.append(pair)
    with DATASET_PATH.open("w", encoding="utf-8") as handle:
        for pair in pairs:
            handle.write(json.dumps(pair, ensure_ascii=True) + "\n")
    return DATASET_PATH, len(pairs)


def run_finetune(
    epochs: float = 1.0,
    max_steps: int | None = None,
    model_id: str = BASE_MODEL,
) -> Path:
    dataset_path, count = write_dataset()
    if count < 20:
        raise RuntimeError("Need at least 20 script lines before fine-tuning.")
    logger.info("Wrote {} training pairs to {}", count, dataset_path)

    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        raise RuntimeError(
            "Fine-tune extras are missing. From the repo run: "
            "python -m uv sync --extra finetune"
        ) from exc

    if not torch.cuda.is_available():
        raise RuntimeError("Fine-tuning needs a CUDA GPU. This box has none visible.")

    free_gb = torch.cuda.mem_get_info()[0] / 1024**3
    if free_gb < 5.5:
        raise RuntimeError(
            f"Only {free_gb:.1f} GB VRAM free. Close the TUI and Ollama, then run again."
        )

    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=quant,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(
        model,
        LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=("q_proj", "k_proj", "v_proj", "o_proj"),
        ),
    )

    dataset = load_dataset("json", data_files=str(dataset_path), split="train")

    def to_text(row: dict[str, object]) -> dict[str, str]:
        messages = row["messages"]
        if hasattr(tokenizer, "apply_chat_template"):
            text = tokenizer.apply_chat_template(messages, tokenize=False)
        else:
            text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)  # type: ignore[index]
        return {"text": text}

    dataset = dataset.map(to_text, remove_columns=dataset.column_names)

    steps = max_steps if max_steps is not None else max(60, min(400, count))
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=str(OUTPUT_DIR / "runs"),
            num_train_epochs=epochs,
            max_steps=steps,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            learning_rate=2e-4,
            logging_steps=5,
            save_steps=steps,
            bf16=torch.cuda.is_bf16_supported(),
            fp16=not torch.cuda.is_bf16_supported(),
            max_length=384,
            dataset_text_field="text",
            report_to=[],
        ),
        processing_class=tokenizer,
    )
    trainer.train()
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(ADAPTER_DIR)
    tokenizer.save_pretrained(ADAPTER_DIR)
    logger.info("Saved LoRA adapter to {}", ADAPTER_DIR.resolve())
    return ADAPTER_DIR


def serve_adapter(host: str = "127.0.0.1", port: int = DEFAULT_PORT, model_id: str = BASE_MODEL) -> None:
    if not ADAPTER_DIR.is_dir():
        raise RuntimeError("No adapter yet. Run: python -m uv run glados finetune")

    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TextIteratorStreamer

    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR)
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )
    model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=quant, device_map="auto")
    model = PeftModel.from_pretrained(model, str(ADAPTER_DIR))
    model.eval()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.rstrip("/") != "/health":
                self.send_error(404)
                return
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if self.path.rstrip("/") != "/v1/chat/completions":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            messages = payload.get("messages", [])
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
            eos_ids = [tokenizer.eos_token_id]
            for name in ("<|im_end|>", "<|im_start|>", "<|eot_id|>"):
                token_id = tokenizer.convert_tokens_to_ids(name)
                if isinstance(token_id, int) and token_id not in eos_ids:
                    eos_ids.append(token_id)
            thread = Thread(
                target=model.generate,
                kwargs={
                    **inputs,
                    "streamer": streamer,
                    "max_new_tokens": 120,
                    "do_sample": True,
                    "temperature": 0.7,
                    "repetition_penalty": 1.15,
                    "eos_token_id": eos_ids,
                    "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
                },
                daemon=True,
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            thread.start()
            leaked = False
            for token in streamer:
                if leaked:
                    continue
                lower = token.casefold()
                if any(mark in lower for mark in ("<|im_start|>", "<|im_end|>", "uservoice", "assistantvoice")):
                    leaked = True
                    continue
                if token.strip().casefold() in {"user", "assistant", "system"}:
                    leaked = True
                    continue
                chunk = json.dumps({"choices": [{"delta": {"content": token}}]})
                self.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            thread.join(timeout=5)

        def log_message(self, format: str, *args: object) -> None:
            logger.info(format, *args)

    logger.info("Serving fine-tuned GLaDOS at http://{}:{}/v1/chat/completions", host, port)
    logger.info("Point completion_url at that URL and set llm_model to glados-lora.")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
