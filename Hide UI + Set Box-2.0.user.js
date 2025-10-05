// ==UserScript==
// @name         Hide UI + Set Box
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Floating button to hide UI elements on wplace.live with box creation
// @match        https://wplace.live/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    const selectors = [
        'div.rounded-t-box.bg-base-100.border-base-300.w-full.border-t.py-3',
        'div.absolute.left-2.top-2.z-30.flex.flex-col.gap-3',
        'div.absolute.bottom-3.right-3.z-30',
        'div.absolute.bottom-3.left-3.z-30',
        'div.absolute.right-2.top-2.z-30',
    ];

    let uiHidden = false;
    let settingBox = false;
    let boxCorners = [];
    let savedBox = null;
    let boxElement = null;
    let mousePos = { x: 0, y: 0 };

    function hideUI() {
        if (!uiHidden) return;
        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(div => div.setAttribute("hidden", ""));
        });
    }

    function showUI() {
        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(div => div.removeAttribute("hidden"));
        });
    }

    const observerUI = new MutationObserver(() => {
        if (uiHidden) hideUI();
    });
    observerUI.observe(document.body, { childList: true, subtree: true });

    // Suivre la position de la souris en temps réel
    document.addEventListener("mousemove", (e) => {
        mousePos.x = e.clientX;
        mousePos.y = e.clientY;
    });

    // Création du conteneur principal
    const container = document.createElement("div");
    container.style.position = "fixed";
    container.style.bottom = "20px";
    container.style.right = "20px";
    container.style.zIndex = "9999";
    container.style.background = "rgba(20,20,20,0.9)";
    container.style.padding = "10px";
    container.style.border = "1px solid #555";
    container.style.borderRadius = "8px";
    container.style.userSelect = "none";
    container.style.color = "#fff";
    container.style.fontFamily = "Arial, sans-serif";
    container.style.fontSize = "14px";
    container.style.cursor = "grab";

    // Bouton Hide UI
    const btnUI = document.createElement("button");
    btnUI.innerText = "Hide UI: OFF";
    styleBtn(btnUI);
    btnUI.addEventListener("click", () => {
        uiHidden = !uiHidden;
        if (uiHidden) {
            btnUI.innerText = "Hide UI: ON";
            hideUI();
        } else {
            btnUI.innerText = "Hide UI: OFF";
            showUI();
        }
    });
    container.appendChild(btnUI);

    // Bouton Set Box
    const btnSetBox = document.createElement("button");
    btnSetBox.innerText = "Set Box";
    styleBtn(btnSetBox);
    btnSetBox.addEventListener("click", () => {
        settingBox = !settingBox;
        boxCorners = [];
        if (settingBox) {
            btnSetBox.innerText = "Cancel Box";
            btnSetBox.style.background = "#442222";
            alert("Appuyez sur F deux fois pour définir les coins (haut-gauche, puis bas-droite)");
        } else {
            btnSetBox.innerText = "Set Box";
            btnSetBox.style.background = "#222";
        }
    });
    container.appendChild(btnSetBox);

    // Bouton Show Box
    const btnShowBox = document.createElement("button");
    btnShowBox.innerText = "Show Box: OFF";
    styleBtn(btnShowBox);
    btnShowBox.addEventListener("click", () => {
        if (!savedBox) {
            alert("Aucune box n'a été définie. Utilisez 'Set Box' d'abord.");
            return;
        }
        toggleBox();
    });
    container.appendChild(btnShowBox);

    document.body.appendChild(container);

    // Fonction pour styliser les boutons
    function styleBtn(btn) {
        btn.style.margin = "4px 0";
        btn.style.padding = "6px 10px";
        btn.style.background = "#222";
        btn.style.color = "#fff";
        btn.style.border = "1px solid #555";
        btn.style.borderRadius = "6px";
        btn.style.cursor = "pointer";
        btn.style.fontSize = "13px";
        btn.style.width = "140px";
        btn.style.opacity = "0.85";
        btn.addEventListener("mouseenter", () => btn.style.opacity = "1");
        btn.addEventListener("mouseleave", () => btn.style.opacity = "0.85");
    }

    // Écouter les touches F pour définir les coins
    document.addEventListener("keydown", (e) => {
        if (e.key === "f" && settingBox && boxCorners.length < 2) {
            e.preventDefault();

            // Utiliser la position actuelle de la souris
            boxCorners.push({ x: mousePos.x, y: mousePos.y });

            if (boxCorners.length === 1) {
                console.log("Premier coin défini:", boxCorners[0]);
                alert(`Premier coin défini à (${boxCorners[0].x}, ${boxCorners[0].y})`);
            } else if (boxCorners.length === 2) {
                console.log("Deuxième coin défini:", boxCorners[1]);
                createBox();
                settingBox = false;
                btnSetBox.innerText = "Set Box";
                btnSetBox.style.background = "#222";
            }
        }
    });

    // Créer la box à partir des deux coins
    function createBox() {
        const x1 = Math.min(boxCorners[0].x, boxCorners[1].x);
        const y1 = Math.min(boxCorners[0].y, boxCorners[1].y);
        const x2 = Math.max(boxCorners[0].x, boxCorners[1].x);
        const y2 = Math.max(boxCorners[0].y, boxCorners[1].y);

        savedBox = {
            left: x1,
            top: y1,
            width: x2 - x1,
            height: y2 - y1
        };

        console.log("Box sauvegardée:", savedBox);
        alert(`Box créée: ${savedBox.width}x${savedBox.height}px à la position (${savedBox.left}, ${savedBox.top})`);
    }

    // Afficher/masquer la box
    function toggleBox() {
        if (boxElement) {
            // Masquer la box
            boxElement.remove();
            boxElement = null;
            btnShowBox.innerText = "Show Box: OFF";
        } else {
            // Afficher la box
            boxElement = document.createElement("div");
            boxElement.style.position = "fixed";
            boxElement.style.left = savedBox.left + "px";
            boxElement.style.top = savedBox.top + "px";
            boxElement.style.width = savedBox.width + "px";
            boxElement.style.height = savedBox.height + "px";
            boxElement.style.border = "3px solid #ff0000";
            boxElement.style.background = "rgba(255, 0, 0, 0.1)";
            boxElement.style.zIndex = "9998";
            boxElement.style.pointerEvents = "none";
            document.body.appendChild(boxElement);
            btnShowBox.innerText = "Show Box: ON";
        }
    }

    // Système de drag pour déplacer le conteneur
    let offsetX, offsetY;
    container.addEventListener("mousedown", (e) => {
        if (e.target.tagName === "BUTTON") return;
        container.dragging = true;
        offsetX = e.clientX - container.getBoundingClientRect().left;
        offsetY = e.clientY - container.getBoundingClientRect().top;
        container.style.cursor = "grabbing";
        document.addEventListener("mousemove", move);
        document.addEventListener("mouseup", stop);
    });

    function move(e) {
        container.style.left = (e.clientX - offsetX) + "px";
        container.style.top = (e.clientY - offsetY) + "px";
        container.style.right = "auto";
        container.style.bottom = "auto";
        container.style.position = "fixed";
    }

    function stop() {
        container.dragging = false;
        container.style.cursor = "grab";
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", stop);
    }
})();