# 🚀 Quick Start: Test Your Chatbot Locally

## ✅ Your System is Ready!

All checks passed:
- ✅ Virtual environment configured
- ✅ Dependencies installed
- ✅ Weaviate connection working
- ✅ Environment variables set

## 🎯 How to Test (3 Easy Steps)

### Step 1: Start the Server

Open a terminal and run:

```bash
cd /Users/desh/document-ai
source .venv/bin/activate
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

Keep this terminal open!

---

### Step 2: Test the Chatbot

Open a **NEW terminal** and run:

```bash
cd /Users/desh/document-ai
source .venv/bin/activate
python test_client.py
```

---

### Step 3: Try These Commands

In the interactive client:

#### Upload a PDF:
```
/upload /path/to/your/document.pdf
```

#### Ask Questions:
```
What are the main terms in the contract?
Can you summarize the document?
Explain clause 5
```

#### Check Stats:
```
/stats
```

#### Exit:
```
/quit
```

---

## 🌐 Alternative: Use the Web Interface

Open your browser and go to:

**http://127.0.0.1:8000/docs**

This gives you an interactive interface to:
- Upload PDFs
- Chat with the bot
- Test all endpoints

---

## 📝 Example Session

```
Terminal 1 (Server):
$ cd /Users/desh/document-ai
$ source .venv/bin/activate
$ python main.py
INFO: Uvicorn running on http://127.0.0.1:8000

Terminal 2 (Client):
$ cd /Users/desh/document-ai
$ source .venv/bin/activate
$ python test_client.py

👤 Enter your tenant ID: alice

💬 You: /upload contract.pdf
📤 Uploading PDF: contract.pdf
✅ Upload successful! Chunks processed: 25

💬 You: What are the key terms in this contract?
🤖 AI: Based on the contract, the key terms include...

💬 You: Who are the parties involved?
🤖 AI: The parties involved are...

💬 You: /quit
👋 Goodbye!
```

---

## 🔧 Troubleshooting

### Server won't start?
Check if port 8000 is in use:
```bash
lsof -i :8000
```

### Can't upload PDF?
Make sure Tesseract OCR is installed:
```bash
brew install tesseract
```

### Need help?
Run the quick setup check:
```bash
python quick_setup.py
```

---

## 📚 Documentation

- **Full Testing Guide**: `TESTING_GUIDE.md`
- **Weaviate Details**: `WEAVIATE_INTEGRATION.md`
- **Main README**: `README.md`
- **API Docs**: http://127.0.0.1:8000/docs (when server is running)

---

## 🎉 You're All Set!

Your Document AI Chatbot is ready to use. Start the server and begin testing!

**Questions?** Check the documentation files or the inline help in the test client.

