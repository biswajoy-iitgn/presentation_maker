# SlideVQA access and inventory notes

Identity: SlideVQA, the multi-image document visual question-answering dataset from the AAAI 2023 paper.

Sources inspected:

- GitHub repository: https://github.com/nttmdlab-nlp/SlideVQA
- Hugging Face dataset: https://huggingface.co/datasets/NTT-hil-insight/SlideVQA
- GitHub revision at inventory time: `0d4168a935d60b0b218097205a02fb1133c8bead`
- Hugging Face revision at inventory time: `e780ea258d734958befbfaed19fa059584642ca8`

The repository README reports 14,484 question-answer pairs, 890,945 bounding boxes, and 2,619 slide decks with 20 images per deck. It describes QA and bounding-box annotations separately. The GitHub source says image OCR needs a separate extraction step (Google Cloud Vision in the experiments or Tesseract); OCR is not part of the Hugging Face feature list. The Hub card lists `train` (10,617 rows), `val` (1,652), and `test` (2,215), totalling 14,484. It includes 20 image columns and QA fields, but not bounding-box or OCR fields.

No dataset files were acquired. The Hub requires accepting NTT's evaluation agreement and sharing contact details. The public GitHub `LICENSE` also makes access/use conditional on that agreement. The Hub estimates 10,904,324,390 download bytes and 36,683,137,812.92 dataset bytes, so the Hub release also exceeds this acquisition's 10 GiB budget. No terms were accepted and no registration information was submitted.

Status: `approval_required`. Missing components: images, QA payload, bounding-box annotations, OCR outputs, and any dependencies needed to reconstruct the full dataset.
