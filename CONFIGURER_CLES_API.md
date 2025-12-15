# 🔑 CONFIGURATION DES CLÉS API

## ⚠️ ERREUR: 401 Unauthorized

Vous devez configurer vos clés API pour que l'application fonctionne.

---

## 📋 ÉTAPES:

### 1. OpenRouter API (pour les LLMs)
1. Allez sur: **https://openrouter.ai/keys**
2. Créez un compte (gratuit)
3. Cliquez sur "Create Key"
4. Copiez la clé (format: `sk-or-v1-...`)
5. Ouvrez `configs/app.yaml`
6. Remplacez `VOTRE_CLE_ICI` par votre clé dans les 3 endroits:
   - `models.planner.api_key`
   - `models.synthesizer.api_key`
   - `models.reflector.api_key`

### 2. Brave Search API (pour la recherche web)
1. Allez sur: **https://brave.com/search/api/**
2. Créez un compte
3. Obtenez votre clé API
4. Dans `configs/app.yaml`, remplacez:
   ```yaml
   search:
     brave:
       api_key: "VOTRE_CLE_BRAVE_ICI"
   ```

---

## 💡 MODÈLES GRATUITS UTILISÉS:
- `mistralai/devstral-2512:free` - Gratuit sur OpenRouter!

---

## ✅ APRÈS LA CONFIGURATION:
1. Sauvegardez `configs/app.yaml`
2. Redémarrez le serveur (fermez et relancez `START_SERVER.bat`)
3. L'application devrait fonctionner!

---

## 🆘 BESOIN D'AIDE?
Si vous n'avez pas de clé API, vous pouvez utiliser Ollama en local (pas de clé nécessaire).
