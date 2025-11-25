from dataclasses import dataclass

from tqdm import tqdm

from graphgen.bases.datatypes import QAPair


@dataclass
class RewardEvaluator:
    """
    Reward Model Evaluator.
    OpenAssistant/reward-model-deberta-v3-large-v2: 分数范围为[-inf, inf]，越高越好
    """

    reward_name: str = "OpenAssistant/reward-model-deberta-v3-large-v2"
    max_length: int = 2560
    results: list[float] = None

    def __post_init__(self):
        import torch

        self.num_gpus = torch.cuda.device_count()

    @staticmethod
    def _get_hf_cache_dir():
        """获取 HuggingFace 缓存目录"""
        import os
        current_file = os.path.abspath(__file__)
        # 从 graphgen/models/evaluator/reward_evaluator.py 向上4级到项目根目录
        project_root = os.path.abspath(os.path.join(current_file, "..", "..", "..", ".."))
        hf_cache_dir = os.path.join(project_root, "models", "huggingface")
        os.makedirs(hf_cache_dir, exist_ok=True)
        return hf_cache_dir

    @staticmethod
    def process_chunk(rank, pairs, reward_name, max_length, return_dict):
        import torch
        import os
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        device = f"cuda:{rank}"
        torch.cuda.set_device(rank)

        # 设置缓存目录
        hf_cache_dir = RewardEvaluator._get_hf_cache_dir()
        if "TRANSFORMERS_CACHE" not in os.environ:
            os.environ["TRANSFORMERS_CACHE"] = hf_cache_dir
        if "HF_HOME" not in os.environ:
            os.environ["HF_HOME"] = hf_cache_dir

        rank_model = AutoModelForSequenceClassification.from_pretrained(reward_name, cache_dir=hf_cache_dir)
        tokenizer = AutoTokenizer.from_pretrained(reward_name, cache_dir=hf_cache_dir)
        rank_model.to(device)
        rank_model.eval()

        results = []
        with torch.no_grad():
            for pair in tqdm(pairs):
                inputs = tokenizer(
                    pair.question,
                    pair.answer,
                    return_tensors="pt",
                    max_length=max_length,
                    truncation=True,
                )
                inputs = {k: v.to(device) for k, v in inputs.items()}
                score = rank_model(**inputs).logits[0].item()
                results.append(score)

        return_dict[rank] = results

    def evaluate(self, pairs: list[QAPair]) -> list[float]:
        import torch.multiprocessing as mp

        chunk_size = len(pairs) // self.num_gpus
        chunks = []
        for i in range(self.num_gpus):
            start = i * chunk_size
            end = start + chunk_size
            if i == self.num_gpus - 1:
                end = len(pairs)
            chunks.append(pairs[start:end])

        # multi-process
        manager = mp.Manager()
        return_dict = manager.dict()
        processes = []

        for rank, chunk in enumerate(chunks):
            p = mp.Process(
                target=self.process_chunk,
                args=(rank, chunk, self.reward_name, self.max_length, return_dict),
            )
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        # 合并结果
        results = []
        for rank in range(len(chunks)):
            results.extend(return_dict[rank])

        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join()

        return results

    def get_average_score(self, pairs: list[QAPair]) -> float:
        """
        Get the average score of a batch of texts.
        """
        results = self.evaluate(pairs)
        self.results = results
        return sum(self.results) / len(pairs)

    def get_min_max_score(self, pairs: list[QAPair]) -> tuple[float, float]:
        """
        Get the min and max score of a batch of texts.
        """
        if self.results is None:
            self.get_average_score(pairs)
        return min(self.results), max(self.results)
