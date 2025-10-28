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
  payload.bullets.forEach((bullet) => {
    const li = document.createElement("li");
    li.textContent = bullet.text;
    bulletsList.appendChild(li);
  });
  if (payload.sources.length) {
    const links = payload.sources
      .map((source) => `[${source.label}] <a href="${source.url}" target="_blank" rel="noopener">${source.title}</a>`)
      .join("<br/>");
    sourcesDiv.innerHTML = `<h3>Sources</h3>${links}`;
  } else {
    sourcesDiv.innerHTML = "";
  }
  metadataPre.textContent = JSON.stringify(payload.metadata, null, 2);
  resultsSection.classList.remove("hidden");
}

function toggleLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Running..." : "Run";
}
