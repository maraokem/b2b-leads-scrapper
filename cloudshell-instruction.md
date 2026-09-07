```markdown
# Running on Google Cloud Shell or Linux

Install Xvfb, which provides a virtual display for headful browser execution:

```bash
sudo apt update
sudo apt install -y xvfb
```

Run the application with Xvfb:

```bash
xvfb-run -a python main.py
```
```