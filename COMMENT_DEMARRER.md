# INSTRUCTIONS POUR DÉMARRER L'APPLICATION

## ⚠️ IMPORTANT: N'utilisez PAS Live Server!

### Pour démarrer l'application:

1. **Double-cliquez sur `START_SERVER.bat`**
   - OU ouvrez Command Prompt et tapez:
   ```cmd
   cd C:\Users\AzComputer\Documents\projects\AI-Digest-Agent
   python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
   ```

2. **Attendez 30-40 secondes** que les modèles se chargent
   - Vous verrez: "Uvicorn running on http://127.0.0.1:8000"

3. **Ouvrez votre navigateur** et allez à:
   ```
   http://127.0.0.1:8000/ui/index.html
   ```

4. **Testez avec une question!**

---

## ❌ NE FAITES PAS:
- N'utilisez PAS Live Server de VS Code
- N'ouvrez PAS `index.html` directement
- N'allez PAS sur le port 5500

## ✅ FAITES:
- Lancez `START_SERVER.bat`
- Allez sur `http://127.0.0.1:8000/ui/index.html`

---

Le serveur FastAPI sert à la fois l'API ET l'interface web.
