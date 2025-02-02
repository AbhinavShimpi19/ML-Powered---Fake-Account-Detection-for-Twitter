document.getElementById("monitorForm").addEventListener("submit", function (event) {
    event.preventDefault();
    const profilesInput = document.getElementById("profiles").value;
    const profiles = profilesInput.split(",").map(profile => profile.trim());
    
    fetch("/monitor", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ profiles: profiles })
    })
    .then(response => response.json())
    .then(data => {
        const resultsDiv = document.getElementById("results");
        resultsDiv.innerHTML = ""; // Clear previous results

        data.forEach(profile => {
            const profileDiv = document.createElement("div");
            // Display only the status
            profileDiv.innerHTML = `
                <strong>Status:</strong> ${profile.status} <br>
                <hr>
            `;
            resultsDiv.appendChild(profileDiv);
        });
    })
    .catch(error => {
        console.error("Error:", error);
    });
});
