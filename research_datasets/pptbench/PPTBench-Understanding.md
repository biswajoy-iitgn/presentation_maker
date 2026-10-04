
# PPTBench Understanding Dataset

A collection of PowerPoint slides with associated understanding tasks and metadata.

## Dataset Structure

The dataset contains the following fields for each entry:
- `hash`: Unique identifier for each slide
- `category`: Category/topic of the slide
- `task`: Understanding task associated with the slide
- `description`: Description of the slide content
- `question`: Question formulated for the slide

## Usage

### Loading the Dataset
You can load this dataset using the Hugging Face Datasets library:

```python
from datasets import load_dataset

dataset = load_dataset("tyrionhuu/PPTBench-Understanding")
