# CVAT

## Installation

```bash
conda create -n cvat_2.47.0 conda-forge::cvat-cli=2.47.0 conda-forge::cvat-sdk=2.47.0 anaconda::jupyter --solver libmamba
```

```bash
$ conda activate cvat_2.47.0
$ python --version
Python 3.13.9
$ python -c "import cvat_sdk; print(cvat_sdk.__version__)"
2.47.0
$ cvat-cli --version
2.47.0
```
