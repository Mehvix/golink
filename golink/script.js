const btn = document.querySelector(".btn-toggle");
const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)");



let currentTheme = localStorage.getItem("theme");

if (currentTheme == "light") {
    document.body.classList.toggle("light-theme");
    btn.checked = false;
} else {    // if (currentTheme == "dark")
    document.body.classList.toggle("dark-theme");
    btn.checked = true;
}

btn.addEventListener("click", function () {
    if (prefersDarkScheme.matches) {
        document.body.classList.toggle("light-theme");
        var theme = document.body.classList.contains("light-theme")
            ? "light"
            : "dark";
    } else {
        document.body.classList.toggle("dark-theme");
        var theme = document.body.classList.contains("dark-theme")
            ? "dark"
            : "light";
    }
    localStorage.setItem("theme", theme);
});

// Sorting
// Source: https://stackoverflow.com/a/49041392

const getCellValue = (tr, idx) => tr.children[idx].innerText || tr.children[idx].textContent;

const comparer = (idx, asc) => (a, b) => ((v1, v2) =>
    v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2)
)(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));


document.addEventListener("DOMContentLoaded", function () {
    let lastClickedTh = null;

    document.querySelectorAll("th").forEach(th => {
        th.addEventListener("click", function () {
            if (lastClickedTh) {
                lastClickedTh.classList.remove("active");
            }
            lastClickedTh = th;
            th.classList.add("active");

            const table = th.closest('table');
            Array.from(table.querySelectorAll('tr:nth-child(n+2)'))
                .sort(comparer(Array.from(th.parentNode.children).indexOf(th), this.asc = !this.asc))
                .forEach(tr => table.appendChild(tr));
        });
    });

    document.querySelector("th:nth-child(2)").click();
});