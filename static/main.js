document.getElementById("submitBtn").addEventListener("click", async function () {
    const articleText = document.getElementById("article").value;
    const urlText = document.getElementById("url").value;
    const question = document.getElementById("question").value;

    const response = await fetch("/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ article_text: articleText, url: urlText, question: question }),
    });

    const responseData = await response.json();
    document.getElementById("answer").textContent = responseData.answer;

    // Clear input fields after submitting
    document.getElementById("article").value = '';
    document.getElementById("url").value = '';
    document.getElementById("question").value = '';
});

document.getElementById("saveFlashcardBtn").addEventListener("click", function () {
    const question = document.getElementById("question").value;
    const answer = document.getElementById("answer").textContent;
    const flashcard = document.createElement("li");
    flashcard.style.display = "flex";
    flashcard.style.justifyContent = "space-between";
    flashcard.style.marginBottom = "1rem";

    const answerDiv = document.createElement("div");
    answerDiv.textContent = `A: ${answer}`;
    answerDiv.style.display = "inline-block";
    answerDiv.style.width = "49%";
    answerDiv.style.textAlign = "left";
    answerDiv.style.backgroundColor = "#000";
    answerDiv.style.border = "1px solid #ccc";
    answerDiv.style.borderRadius = "4px";
    answerDiv.style.padding = "0.5rem";
    flashcard.appendChild(answerDiv);

    const questionDiv = document.createElement("div");
    questionDiv.textContent = `Q: ${question}`;
    questionDiv.style.display = "inline-block";
    questionDiv.style.width = "49%";
    questionDiv.style.textAlign = "left";
    questionDiv.style.backgroundColor = "#000";
    questionDiv.style.border = "1px solid #ccc";
    questionDiv.style.borderRadius = "4px";
    questionDiv.style.padding = "0.5rem";
    flashcard.appendChild(questionDiv);

    document.getElementById("flashcards").appendChild(flashcard);
});
