# Cumo (formerly CalendarCompanion)

## Local Development

### Prerequisites

- Node.js 18+
- Python 3.12+
- npm or yarn

### Setup

1. Install frontend dependencies:
```bash
npm install
```

2. Setup Python backend:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cd ..
```

3. Copy Google OAuth credentials:
```bash
cp backend/credentials.json.example backend/credentials.json
# Edit credentials.json with your Google OAuth client credentials
```

### Run

Start the development server:
```bash
npm run dev
```

The app will open automatically. Use Cmd+/ (or Ctrl+/) to toggle the window.

### Build

Build for production:
```bash
npm run dist
```

Builds will be output to the `dist/` directory.
