async function startCalls() {

    const subject = document.getElementById("subject").value;
    const section = document.getElementById("section").value;
    const rolls = document.getElementById("rolls").value
    .split(/\s|,|\n/)
    .filter(r => r.trim() !== "");

    document.getElementById("status").innerText = "Calling...";

    await fetch("/start-calls", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            subject,
            section,
            rolls
        })
    });

    document.getElementById("status").innerText = "Done!";
}