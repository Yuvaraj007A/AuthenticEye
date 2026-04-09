# AuthenticEye v5.0 Setup & Run Guide

To run the complete AuthenticEye project with all of its integrated components, you need to start three distinct services. We recommend opening three separate terminal windows side-by-side.

### Prerequisites
Make sure you have installed:
*   [Node.js](https://nodejs.org/en/) & npm
*   [Python 3.9+](https://www.python.org/downloads/)
*   (Optional but recommended) A Virtual Environment manager like `venv` or `conda`

> [!WARNING]
> Both Node backend servers and the Python AI services depend on their respective `.env` files. Ensure your environment files are correctly configured based on `.env.example`.

---

## 🟢 Terminal 1: Application Backend (Node.js)
This handles user authentication, dashboard data, project metadata, and generic file-saving actions.

1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Install NodeJS dependencies (only needed the first time):
   ```bash
   npm install
   ```
3. Start the Express server:
   ```bash
   npm run dev
   # OR
   node server.js
   ```
> *Usually runs on `http://localhost:5000`*

---

## 🔵 Terminal 2: Forensic AI Engine (Python FastAPI)
This powers all the deepfake detection logic, including the 6-module fusion classifier, Grad-CAM, and Temporal Video Analysis.

1. Navigate to the `ai-service` folder:
   ```bash
   cd ai-service
   ```
2. Activate your Virtual Environment (highly recommended):
   ```bash
   # On Windows
   venv\Scripts\activate
   # Or create one if it doesn't exist: python -m venv venv
   ```
3. Install Python dependencies (only needed the first time):
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI server via Uvicorn:
   ```bash
   python main.py
   # OR
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
   ```
> *Usually runs on `http://localhost:8000`*

---

## 🟣 Terminal 3: Web Frontend / Dashboard (React + Vite)
This serves the actual user interface and interacts with both the Node Backend and the AI Microservice.

1. Navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install UI dependencies (only needed the first time):
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
> *Usually runs on `http://localhost:5173`*

---

### Verification Checklist
Once all three are running, you can test if everything is talking to each other by performing these checks:

1. **Visit Frontend:** Go to `http://localhost:5173` in your browser.
2. **Test Analytics/Auth:** Try logging in or signing up (tests connection to Terminal 1).
3. **Run AI Diagnostics:** Navigate to the AI forensic tool, upload a demo image/video, and wait for the results. (Tests connection to Terminal 2).

> [!TIP]
> If you have an NVIDIA GPU, make sure `torch` was compiled with CUDA. You can verify this by checking the terminal output of `ai-service/main.py`; it should explicitly print out `Device: cuda`.
