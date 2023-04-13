document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById("image-form");

    form.addEventListener("submit", e => {
        e.preventDefault();

        const formData = new FormData(form);

        fetch("http://127.0.0.1:5000/translate/image", { method: "POST", body: formData, })
            .then(response => response.ok ? response.json() : console.error("Error"))
            .then(data => console.log(data))
            .catch(e => console.error(e))
    });
});
