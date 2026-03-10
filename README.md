# INSTALL

```bash
pip3 install -r requirements.txt
```

# USE

```bash
python3 app.py {file or folder containing the heic files}
```

# ARGS
```
positional arguments:
  input            Source folder or HEIC file to convert.

optional arguments:
  -h, --help       show this help message and exit
  --keep-metadata  Keep metadata in PNG output.
  --optimize       Optimize PNG output for smaller file size.
  --cores [1-8]    Number of CPU cores to use (max {count of your max cpu cores})
```