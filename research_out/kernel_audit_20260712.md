# HumorVibes six-kernel audit

Audited: 2026-07-12T16:36:43.498409+00:00. Competition API deadline: **2026-07-25 04:00:00**.

The operation was read-only: sources and outputs were pulled into a temporary directory; no kernel was rerun or submitted.

| Kernel | Live status | Private | Source cells match | Mirrored outputs match |
|---|---|:---:|:---:|:---:|
| taylorsamarel/humorvibes-measuring-jokes-with-gemma | KernelWorkerStatus.COMPLETE | True | True | True |
| taylorsamarel/humorvibes-mesh-zoo-lab | KernelWorkerStatus.COMPLETE | True | True | True |
| taylorsamarel/humorvibes-corpus-lab | KernelWorkerStatus.COMPLETE | True | True | True |
| taylorsamarel/humorvibes-panel-lab | KernelWorkerStatus.COMPLETE | True | True | True |
| taylorsamarel/humorvibes-validate-ratings | KernelWorkerStatus.COMPLETE | True | True | True |
| taylorsamarel/humorvibes-studio-g2 | KernelWorkerStatus.COMPLETE | True | True | True |

## Attached inference sources

- `taylorsamarel/humorvibes-measuring-jokes-with-gemma`: `google/gemma-2/Transformers/gemma-2-2b-it/2`
- `taylorsamarel/humorvibes-mesh-zoo-lab`: `google/gemma-2/Transformers/gemma-2-2b-it/2`, `google/gemma-3/Transformers/gemma-3-1b-it/1`, `metaresearch/llama-3.2/Transformers/3b-instruct/1`, `qwen-lm/qwen2.5/Transformers/1.5b-instruct/1`
- `taylorsamarel/humorvibes-corpus-lab`: `google/gemma-2/Transformers/gemma-2-2b-it/2`
- `taylorsamarel/humorvibes-panel-lab`: `google/gemma-2/Transformers/gemma-2-2b-it/2`
- `taylorsamarel/humorvibes-validate-ratings`: `google/gemma-2/Transformers/gemma-2-2b-it/2`
- `taylorsamarel/humorvibes-studio-g2`: `google/gemma-2/Transformers/gemma-2-2b-it/2`

Every existing research output named in the writeup is byte-identical to the latest Kaggle output. Raw notebook files differ because Kaggle adds execution outputs; normalized code/markdown cells match exactly.

Overall court passed: **True**.
