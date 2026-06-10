async function startCalls() {
    const subject = document.getElementById("subject").value;
    const section = document.getElementById("section").value;

    const rolls = document.getElementById("rolls").value
        .split(/[\s,]+/)
        .filter(r => r.trim() !== "");

    document.getElementById("status").innerText = "📞 Calling parents...";

    const res = await fetch("/start-calls", {
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

    const data = await res.json();

    document.getElementById("status").innerText = "✅ Calls completed!";
}