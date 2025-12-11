const submitButton = document.getElementById("submit");
const questionInput = document.getElementById("question");
const freshOnlyInput = document.getElementById("fresh-only");
const resultsSection = document.getElementById("results");
const bulletsList = document.getElementById("bullets");
const sourcesDiv = document.getElementById("sources");
const metadataPre = document.getElementById("metadata");

const API_BASE = "..";

submitButton.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) {
    alert("Please enter a question.");
    return;
  }
  toggleLoading(true);
  try {
    const response = await fetch(`${API_BASE}/answer`, {
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
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Request failed");
    }
    const payload = await response.json();
    renderResult(payload);
  } catch (error) {
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
