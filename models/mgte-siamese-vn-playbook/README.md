---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- generated_from_trainer
- dataset_size:5000
- loss:CosineSimilarityLoss
base_model: Alibaba-NLP/gte-multilingual-base
widget:
- source_sentence: 105 Trần Xuân Lê, Hòa Khê, Thanh Khê, Đà Nẵng, Việt Nam
  sentences:
  - 136 Tô Hiệu, Phường Phú Thạnh, Thành Phố Hồ Chí Minh, Việt Nam
  - 105 Trần Xuân Lê, Phường Thanh Khê, Thành Phố Đà Nẵng, Việt Nam
  - 6-8 Phan Đăng Lưu, Phường Bình Thạnh, Thành Phố Hồ Chí Minh, Việt Nam
- source_sentence: 551 ĐT713, Đức Hạnh, Đức Linh, Bình Thuận, Việt Nam
  sentences:
  - Đường Hoàng Quốc Việt, Phường Buôn Hồ, Tỉnh Đắk Lắk, Việt Nam
  - 5 Đường Trần Hưng Đạo, Phường Phúc Yên, Tỉnh Phú Thọ, Việt Nam
  - 551 ĐT713, Xã Hoài Đức, Tỉnh Lâm Đồng, Việt Nam
- source_sentence: 43CT Tam Đảo, Phường 15, Quận 10, Thành phố Hồ Chí Minh, Việt Nam
  sentences:
  - 3/1 H Tổ 8 Kp6, Phường Đông Hưng Thuận, Thành Phố Hồ Chí Minh, Việt Nam
  - 43CT Tam Đảo, Phường Hòa Hưng, Thành Phố Hồ Chí Minh, Việt Nam
  - 291A Đ. Bến Vân Đồn, Phường Vĩnh Hội, Thành Phố Hồ Chí Minh, Việt Nam
- source_sentence: 280/70/40 Đ. Bùi Hữu Nghĩa, Phường 2, Bình Thạnh, Hồ Chí Minh,
    Việt Nam
  sentences:
  - 112, 1 Mễ Cốc, Phường Phú Định, Thành Phố Hồ Chí Minh, Việt Nam
  - 1/50 Đường số 8, Phường Tăng Nhơn Phú, Thành Phố Hồ Chí Minh, Việt Nam
  - 280/70/40 Đ. Bùi Hữu Nghĩa, Phường Gia Định, Thành Phố Hồ Chí Minh, Việt Nam
- source_sentence: 616 Nguyễn Văn Linh, Vĩnh Niệm Lê Chân, Hải Phòng, Việt Nam
  sentences:
  - Nhà Thuốc FPT Long Châu, 65 Quang Trung, Phường Hạc Thành, Tỉnh Thanh Hóa, Việt
    Nam
  - Máy Tính Tùng Lương, đường giãn dân mới, Xã Yên Mỹ, Tỉnh Hưng Yên, Việt Nam
  - 616 Nguyễn Văn Linh, Phường An Biên, Thành Phố Hải Phòng, Việt Nam
pipeline_tag: sentence-similarity
library_name: sentence-transformers
---

# SentenceTransformer based on Alibaba-NLP/gte-multilingual-base

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [Alibaba-NLP/gte-multilingual-base](https://huggingface.co/Alibaba-NLP/gte-multilingual-base). It maps sentences & paragraphs to a 768-dimensional dense vector space and can be used for retrieval.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [Alibaba-NLP/gte-multilingual-base](https://huggingface.co/Alibaba-NLP/gte-multilingual-base) <!-- at revision 9bbca17d9273fd0d03d5725c7a4b0f6b45142062 -->
- **Maximum Sequence Length:** 8192 tokens
- **Output Dimensionality:** 768 dimensions
- **Similarity Function:** Cosine Similarity
- **Supported Modality:** Text
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'transformer_task': 'feature-extraction', 'modality_config': {'text': {'method': 'forward', 'method_output_name': 'last_hidden_state'}}, 'module_output_name': 'token_embeddings', 'architecture': 'NewModel'})
  (1): Pooling({'embedding_dimension': 768, 'pooling_mode': 'cls', 'include_prompt': True})
  (2): Normalize({})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```
Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    '616 Nguyễn Văn Linh, Vĩnh Niệm Lê Chân, Hải Phòng, Việt Nam',
    '616 Nguyễn Văn Linh, Phường An Biên, Thành Phố Hải Phòng, Việt Nam',
    'Máy Tính Tùng Lương, đường giãn dân mới, Xã Yên Mỹ, Tỉnh Hưng Yên, Việt Nam',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 768]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.9997, 0.9945],
#         [0.9997, 1.0000, 0.9945],
#         [0.9945, 0.9945, 1.0000]])
```
<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 5,000 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence_0                                                                        | sentence_1                                                                        | label                                                         |
  |:--------|:----------------------------------------------------------------------------------|:----------------------------------------------------------------------------------|:--------------------------------------------------------------|
  | type    | string                                                                            | string                                                                            | float                                                         |
  | details | <ul><li>min: 4 tokens</li><li>mean: 22.51 tokens</li><li>max: 52 tokens</li></ul> | <ul><li>min: 6 tokens</li><li>mean: 21.95 tokens</li><li>max: 45 tokens</li></ul> | <ul><li>min: 1.0</li><li>mean: 1.0</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence_0                                                                               | sentence_1                                                                                      | label            |
  |:-----------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------|:-----------------|
  | <code>62 Diên Hồng, Lê Hồng Phong, Thành phố Qui Nhơn, Bình Định 590000, Việt Nam</code> | <code>62 Diên Hồng, Lê Hồng Phong, Phường Quy Nhơn, Tỉnh Gia Lai, Việt Nam</code>               | <code>1.0</code> |
  | <code>Clb Khiêu Vũ, 112 Bùi Quang Là, Phường 12, Gò Vấp, Hồ Chí Minh</code>              | <code>Clb Khiêu Vũ, 112 Bùi Quang Là, Phường An Hội Tây, Thành Phố Hồ Chí Minh, Việt Nam</code> | <code>1.0</code> |
  | <code>68, Cao Thắng, Phường Nam Hà, Nam Hà, Hà Tĩnh Hà Tĩnh, Việt Nam</code>             | <code>68, Cao Thắng, Phường Thành Sen, Tỉnh Hà Tĩnh, Việt Nam</code>                            | <code>1.0</code> |
* Loss: [<code>CosineSimilarityLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#cosinesimilarityloss) with these parameters:
  ```json
  {
      "loss_fct": "torch.nn.modules.loss.MSELoss",
      "cos_score_transformation": "torch.nn.modules.linear.Identity"
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 32
- `per_device_eval_batch_size`: 32
- `num_train_epochs`: 1
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `overwrite_output_dir`: False
- `do_predict`: False
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 32
- `per_device_eval_batch_size`: 32
- `per_gpu_train_batch_size`: None
- `per_gpu_eval_batch_size`: None
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 5e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1
- `num_train_epochs`: 1
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: {}
- `warmup_ratio`: 0.0
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `save_safetensors`: True
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `no_cuda`: False
- `use_cpu`: False
- `use_mps_device`: False
- `seed`: 42
- `data_seed`: None
- `jit_mode_eval`: False
- `bf16`: False
- `fp16`: False
- `fp16_opt_level`: O1
- `half_precision_backend`: auto
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: 0
- `ddp_backend`: None
- `tpu_num_cores`: None
- `tpu_metrics_debug`: False
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `past_index`: -1
- `disable_tqdm`: False
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_min_num_params`: 0
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `fsdp_transformer_layer_cls_to_wrap`: None
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `adafactor`: False
- `group_by_length`: False
- `length_column_name`: length
- `project`: huggingface
- `trackio_space_id`: trackio
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `use_legacy_prediction_loop`: False
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_inputs_for_metrics`: False
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `fp16_backend`: auto
- `push_to_hub_model_id`: None
- `push_to_hub_organization`: None
- `mp_parameters`: 
- `auto_find_batch_size`: False
- `full_determinism`: False
- `torchdynamo`: None
- `ray_scope`: last
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_tokens_per_second`: False
- `include_num_input_tokens_seen`: no
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: True
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Time
- **Training**: 30.6 minutes

### Framework Versions
- Python: 3.11.9
- Sentence Transformers: 5.4.1
- Transformers: 4.57.3
- PyTorch: 2.8.0+cpu
- Accelerate: 1.13.0
- Datasets: 4.8.4
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->