name: Build Windows Exe

on:
  push:
    branches: [ "main" ]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v4  # v3 -> v4 yaptık

    - name: Set up Python
      uses: actions/setup-python@v5 # v4 -> v5 yaptık
      with:
        python-version: '3.9'

    - name: Install Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install PyQt6 PyQt6-WebEngine pandas plotly pyinstaller openpyxl

    - name: Build EXE
      run: |
        pyinstaller --noconsole --onefile --name="ProjePaneli" desktop_app.py

    - name: Upload Artifact
      uses: actions/upload-artifact@v4  # Hata veren kısım burasıydı (v3 -> v4)
      with:
        name: ProjePaneli-Windows
        path: dist/ProjePaneli.exe
        compression-level: 0 # İşlemi hızlandırmak için sıkıştırmayı kapatıyoruz (GitHub zaten zip olarak indirtecek)
