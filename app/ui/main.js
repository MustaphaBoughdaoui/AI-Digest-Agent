const submitButton = document.getElementById("submit");
const questionInput = document.getElementById("question");
const freshOnlyInput = document.getElementById("fresh-only");
const resultsSection = document.getElementById("results");
const bulletsList = document.getElementById("bullets");
const sourcesDiv = document.getElementById("sources");
const metadataPre = document.getElementById("metadata");

// Use relative path - works when served from FastAPI
const API_BASE = "..";

submitButton.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) {
    alert("Please enter a question.");
    return;
  }
  toggleLoading(true);
  try {
    let response;
    try {
      response = await fetch(`${API_BASE}/answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          fresh_only: freshOnlyInput.checked,
          max_sources: 8,
        }),
      });
    } catch (networkError) {
      throw new Error("Cannot connect to API server at http://127.0.0.1:8000\n\nPlease start the server:\n1. Open Command Prompt\n2. Run: cd C:\\Users\\AzComputer\\Documents\\projects\\AI-Digest-Agent\n3. Run: python -m uvicorn app.api:app --host 127.0.0.1 --port 8000");
    }

    const text = await response.text();
    
    if (!text || text.trim() === "") {
      throw new Error("Server returned empty response. The API server may have crashed.");
    }

    let payload;
    try {
      payload = JSON.parse(text);
    } catch (parseError) {
      console.error("Invalid response:", text);
      throw new Error("Server returned invalid data. Check if the API server is running correctly on port 8000.");
    }

    if (!response.ok) {
      throw new Error(payload.detail || payload.message || "Request failed");
    }

    renderResult(payload);
  } catch (error) {
    console.error("Error:", error);
    alert(`Error: ${error.message}`);
  } finally {
    toggleLoading(false);
  }
});

function renderResult(payload) {
  bulletsList.innerHTML = "";
  payload.bullets.forEach((bullet, index) => {
    const li = document.createElement("li");
    li.textContent = bullet.text;
    li.style.animationDelay = `${index * 0.1}s`;
    li.classList.add('fade-in-item');
    bulletsList.appendChild(li);
  });
  if (payload.sources.length) {
    const links = payload.sources
      .map((source, index) => `
        <div class="source-item" style="animation-delay: ${index * 0.1}s">
          <span class="source-label">[${source.label}]</span>
          <a href="${source.url}" target="_blank" rel="noopener">
            <i class="fas fa-external-link-alt"></i>
            ${source.title}
          </a>
        </div>
      `)
      .join("");
    sourcesDiv.innerHTML = `<h3>Sources</h3><div class="sources-list">${links}</div>`;
  } else {
    sourcesDiv.innerHTML = "";
  }
  metadataPre.textContent = JSON.stringify(payload.metadata, null, 2);
  resultsSection.classList.remove("hidden");
}

function toggleLoading(isLoading) {
  submitButton.disabled = isLoading;
  const buttonText = submitButton.querySelector('.button-text');
  const spinner = submitButton.querySelector('.spinner');
  if (isLoading) {
    buttonText.textContent = 'Running...';
    spinner.classList.remove('hidden');
  } else {
    buttonText.textContent = 'Run';
    spinner.classList.add('hidden');
  }
}
