/* ==========================================================================
   VINTAGE STRIPE DOC SYSTEM — INTERACTIVE FRONTEND BEHAVIOR
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initCodeBlocks();
    initAlertCallouts();
    initMobileMenu();
    initSearchModal();
});

/* ── 1. THEME SWITCHER STATE MANAGEMENT ───────────────────────────────────── */
function initTheme() {
    const themeToggle = document.getElementById("theme-toggle");
    const htmlEl = document.documentElement;

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const currentTheme = htmlEl.getAttribute("data-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            htmlEl.setAttribute("data-theme", newTheme);
            localStorage.setItem("docs-theme", newTheme);
        });
    }
}

/* ── 2. PREMIUM CODE BLOCK EXTRA FEATURES ─────────────────────────────────── */
function initCodeBlocks() {
    const codeBlocks = document.querySelectorAll(".codehilite");
    
    codeBlocks.forEach(wrapper => {
        // Resolve code language class if present (e.g., class="language-bash")
        const codeElement = wrapper.querySelector("code");
        let langLabel = "terminal";
        
        if (codeElement) {
            const classes = Array.from(codeElement.classList);
            const langClass = classes.find(c => c.startsWith("language-") || c.startsWith("lang-"));
            if (langClass) {
                langLabel = langClass.replace(/^(language-|lang-)/, "").toLowerCase();
            }
        }
        
        // 1. Prepend terminal tab bar
        const headerTab = document.createElement("div");
        headerTab.className = "code-header-tab";
        headerTab.innerHTML = `
            <div class="code-header-dots">
                <span class="code-header-dot"></span>
                <span class="code-header-dot"></span>
                <span class="code-header-dot"></span>
            </div>
            <span class="code-header-lang">${langLabel}</span>
        `;
        wrapper.insertBefore(headerTab, wrapper.firstChild);
        
        // 2. Append copy to clipboard button
        const copyBtn = document.createElement("button");
        copyBtn.className = "btn-copy";
        copyBtn.textContent = "Copy";
        wrapper.appendChild(copyBtn);
        
        copyBtn.addEventListener("click", () => {
            const preElement = wrapper.querySelector("pre");
            if (!preElement) return;
            
            // Clean code block content (exclude tab header text)
            let codeText = preElement.innerText || preElement.textContent;
            
            navigator.clipboard.writeText(codeText).then(() => {
                copyBtn.textContent = "Copied!";
                copyBtn.style.backgroundColor = "var(--success-border)";
                copyBtn.style.color = "#fff";
                
                setTimeout(() => {
                    copyBtn.textContent = "Copy";
                    copyBtn.style.backgroundColor = "";
                    copyBtn.style.color = "";
                }, 2000);
            }).catch(err => {
                console.error("Clipboard copy failed: ", err);
                copyBtn.textContent = "Error";
            });
        });
    });
}

/* ── 3. MARKDOWN ALERT BOXES INJECTOR ────────────────────────────────────── */
function initAlertCallouts() {
    const blockquotes = document.querySelectorAll(".prose blockquote");
    
    blockquotes.forEach(quote => {
        const firstP = quote.querySelector("p");
        if (!firstP) return;
        
        const text = firstP.innerHTML;
        const alertPatterns = {
            "NOTE": { class: "info", title: "Note", icon: "ℹ" },
            "TIP": { class: "success", title: "Tip", icon: "★" },
            "IMPORTANT": { class: "warning", title: "Important", icon: "✦" },
            "WARNING": { class: "warning", title: "Warning", icon: "⚠️" },
            "CAUTION": { class: "warning", title: "Caution", icon: "⚡" }
        };
        
        for (const [key, config] of Object.entries(alertPatterns)) {
            const pattern = `\\[!${key}\\]`;
            const regex = new RegExp(`^\\s*${pattern}\\s*(?:<br>|\\s)*`, "i");
            
            if (regex.test(text)) {
                // Convert blockquote into a styled callout card
                const div = document.createElement("div");
                div.className = `callout ${config.class}`;
                
                // Strip the marker from the text
                const cleanedText = text.replace(regex, "");
                firstP.innerHTML = cleanedText;
                
                // Inject styled structural markup
                div.innerHTML = `
                    <div class="callout-title">
                        <span>${config.icon}</span>
                        <span>${config.title}</span>
                    </div>
                `;
                
                // Move elements from blockquote to the new div
                while (quote.firstChild) {
                    div.appendChild(quote.firstChild);
                }
                
                quote.parentNode.replaceChild(div, quote);
                break;
            }
        }
    });
}

/* ── 4. MOBILE HAMBURGER MENU RESPONSIVENESS ─────────────────────────────── */
function initMobileMenu() {
    const menuToggle = document.getElementById("menu-toggle");
    const sidebarNav = document.querySelector(".sidebar-nav");
    
    if (menuToggle && sidebarNav) {
        menuToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            sidebarNav.classList.toggle("mobile-open");
        });
        
        // Close menu when clicking outside
        document.addEventListener("click", (e) => {
            if (sidebarNav.classList.contains("mobile-open") && !sidebarNav.contains(e.target)) {
                sidebarNav.classList.remove("mobile-open");
            }
        });
    }
}

/* ── 5. COMMAND PALETTE SEARCH MODAL ENGINE ──────────────────────────────── */
function initSearchModal() {
    const searchModal = document.getElementById("search-modal");
    const searchTriggerBtn = document.getElementById("search-trigger-btn");
    const searchInput = document.getElementById("search-input");
    const searchCloseBtn = document.getElementById("search-close-btn");
    const resultsContainer = document.getElementById("search-results-container");
    
    let highlightedIndex = -1;
    let searchDebounceTimer = null;
    
    if (!searchModal) return;

    // Open Modal
    function openModal() {
        searchModal.classList.add("open");
        searchModal.setAttribute("aria-hidden", "false");
        searchInput.focus();
        document.body.style.overflow = "hidden"; // Disable scroll
    }

    // Close Modal
    function closeModal() {
        searchModal.classList.remove("open");
        searchModal.setAttribute("aria-hidden", "true");
        searchInput.value = "";
        resultsContainer.innerHTML = `<div class="search-status">Type to search for config values, tagging options, etc...</div>`;
        highlightedIndex = -1;
        document.body.style.overflow = ""; // Re-enable scroll
    }

    // Toggle on trigger buttons
    if (searchTriggerBtn) {
        searchTriggerBtn.addEventListener("click", openModal);
    }
    if (searchCloseBtn) {
        searchCloseBtn.addEventListener("click", closeModal);
    }

    // Close on clicking backdrop
    searchModal.addEventListener("click", (e) => {
        if (e.target === searchModal) {
            closeModal();
        }
    });

    // Global shortcut listeners (Cmd+K, Ctrl+K, Escape)
    document.addEventListener("keydown", (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === "k") {
            e.preventDefault();
            if (searchModal.classList.contains("open")) {
                closeModal();
            } else {
                openModal();
            }
        }
        
        if (e.key === "Escape" && searchModal.classList.contains("open")) {
            closeModal();
        }
    });

    // Handle typing queries (with debouncing)
    searchInput.addEventListener("input", () => {
        clearTimeout(searchDebounceTimer);
        const query = searchInput.value.trim();
        
        if (!query) {
            resultsContainer.innerHTML = `<div class="search-status">Type to search for config values, tagging options, etc...</div>`;
            highlightedIndex = -1;
            return;
        }

        resultsContainer.innerHTML = `<div class="search-status">Searching...</div>`;

        searchDebounceTimer = setTimeout(() => {
            fetch(`/docs/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(results => {
                    renderSearchResults(results);
                })
                .catch(err => {
                    console.error("Search fetch error: ", err);
                    resultsContainer.innerHTML = `<div class="search-status text-danger">Search failed to run.</div>`;
                });
        }, 200);
    });

    // Render Search Result Cards
    function renderSearchResults(results) {
        resultsContainer.innerHTML = "";
        highlightedIndex = -1;
        
        if (results.length === 0) {
            resultsContainer.innerHTML = `<div class="search-status">No documentation results match your query.</div>`;
            return;
        }

        results.forEach((item, index) => {
            const itemEl = document.createElement("div");
            itemEl.className = "search-result-item";
            itemEl.dataset.url = item.url;
            itemEl.dataset.index = index;

            let snippetsHtml = "";
            if (item.snippets && item.snippets.length > 0) {
                snippetsHtml = `
                    <div class="search-result-snippets">
                        ${item.snippets.map(s => `<span class="search-result-snippet">${s}</span>`).join("")}
                    </div>
                `;
            }

            itemEl.innerHTML = `
                <div class="search-result-title">${item.title}</div>
                ${snippetsHtml}
            `;

            // Click navigation
            itemEl.addEventListener("click", () => {
                window.location.href = item.url;
            });

            resultsContainer.appendChild(itemEl);
        });
    }

    // Keyboard navigation in search results list (Up, Down, Enter)
    searchInput.addEventListener("keydown", (e) => {
        const items = resultsContainer.querySelectorAll(".search-result-item");
        if (items.length === 0) return;

        if (e.key === "ArrowDown") {
            e.preventDefault();
            highlightedIndex = (highlightedIndex + 1) % items.length;
            updateHighlightedItem(items);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            highlightedIndex = (highlightedIndex - 1 + items.length) % items.length;
            updateHighlightedItem(items);
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (highlightedIndex >= 0 && highlightedIndex < items.length) {
                const activeItem = items[highlightedIndex];
                window.location.href = activeItem.dataset.url;
            }
        }
    });

    function updateHighlightedItem(items) {
        items.forEach((item, index) => {
            if (index === highlightedIndex) {
                item.classList.add("highlighted");
                item.scrollIntoView({ block: "nearest" });
            } else {
                item.classList.remove("highlighted");
            }
        });
    }
}
