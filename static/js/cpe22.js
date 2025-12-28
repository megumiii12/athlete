// Popup Elements
const wrapper = document.getElementById("authWrapper");
const loginBox = document.getElementById("loginBox");
const registerBox = document.getElementById("registerBox");

// Safe-guard: elements might not exist if HTML changed
function safe(q) { return document.querySelector(q); }

// Open popup from any .btnlogin-popup (header / hero)
document.querySelectorAll(".btnlogin-popup").forEach(btn => {
    btn.addEventListener("click", (e) => {
        e.preventDefault();
        if (wrapper) {
            wrapper.classList.remove("hidden");
            // default to login view
            if (loginBox) loginBox.classList.remove("hidden");
            if (registerBox) registerBox.classList.add("hidden");
        }
    });
});

// Close popup
if (document.getElementById("closePopup")) {
    document.getElementById("closePopup").addEventListener("click", () => {
        if (wrapper) wrapper.classList.add("hidden");
    });
}

// Switch to register
const regLink = document.querySelector(".register-link");
if (regLink) {
    regLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (loginBox) loginBox.classList.add("hidden");
        if (registerBox) registerBox.classList.remove("hidden");
    });
}

// Switch to login
const loginLink = document.querySelector(".login-link");
if (loginLink) {
    loginLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (registerBox) registerBox.classList.add("hidden");
        if (loginBox) loginBox.classList.remove("hidden");
    });
}

// Toggle Password
function togglePassword(id, icon) {
    const field = document.getElementById(id);
    if (!field) return;
    const eye = icon.querySelector("ion-icon");
    field.type = field.type === "password" ? "text" : "password";
    if (eye) eye.setAttribute("name", field.type === "password" ? "eye" : "eye-off");
}

// API Base
const API_URL = window.location.origin;

// Login Form
if (document.getElementById("loginForm")) {
    document.getElementById("loginForm").addEventListener("submit", async (e) => {
        e.preventDefault();

        const loginEmail = document.getElementById("loginEmail");
        const loginPassword = document.getElementById("loginPassword");

        if (!loginEmail || !loginPassword) return alert("Form fields missing.");

        const email = loginEmail.value.trim();
        const password = loginPassword.value.trim();

        if (!email || !password) return alert("Please enter credentials.");

        try {
            const res = await fetch(`${API_URL}/api/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ email, password })
            });

            const result = await res.json();

            if (result.success) {
                localStorage.setItem("auth_token", result.token);
                localStorage.setItem("username", result.user.username);
                localStorage.setItem("user_id", result.user.id);
                
                // Close popup
                if (wrapper) wrapper.classList.add("hidden");
                // Redirect to dashboard
                window.location.href = "/dashboard";
            } else {
                alert(result.error || "Login failed");
            }
        } catch (err) {
            console.error(err);
            alert("Network error during login");
        }
    });
}

// Register Form
if (document.getElementById("registerForm")) {
    document.getElementById("registerForm").addEventListener("submit", async (e) => {
        e.preventDefault();

        const registerUsername = document.getElementById("registerUsername");
        const registerEmail = document.getElementById("registerEmail");
        const registerPassword = document.getElementById("registerPassword");
        const registerGender = document.getElementById("registerGender");
        const registerAge = document.getElementById("registerAge");

        if (!registerUsername || !registerEmail || !registerPassword || !registerGender || !registerAge) {
            return alert("Form fields missing.");
        }

        const username = registerUsername.value.trim();
        const email = registerEmail.value.trim();
        const password = registerPassword.value.trim();
        const gender = registerGender.value;
        const age = parseInt(registerAge.value);

        if (!username || !email || !password || !age) {
            return alert("Please fill all required fields.");
        }

        if (age < 13 || age > 120) {
            return alert("Please enter a valid age (13-120).");
        }

        try {
            const res = await fetch(`${API_URL}/api/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, email, password, gender, age })
            });

            const result = await res.json();

            if (result.success) {
                alert("Registration successful! Please login.");
                if (registerBox) registerBox.classList.add("hidden");
                if (loginBox) loginBox.classList.remove("hidden");
                // Clear form
                document.getElementById("registerForm").reset();
            } else {
                alert(result.error || "Registration failed");
            }
        } catch (err) {
            console.error(err);
            alert("Network error during registration");
        }
    });
}

// Forgot Password
if (document.getElementById("forgotPassword")) {
    document.getElementById("forgotPassword").addEventListener("click", async (e) => {
        e.preventDefault();
        const email = prompt("Enter your email:");
        if (!email) return;
        const newPass = prompt("New password:");
        const confirmPass = prompt("Confirm new password:");
        if (newPass !== confirmPass) {
            return alert("Passwords do not match.");
        }

        try {
            const res = await fetch(`${API_URL}/api/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, new_password: newPass })
            });

            const result = await res.json();
            alert(result.success ? "Password updated!" : (result.error || "Error"));
        } catch (err) {
            console.error(err);
            alert("Network error while resetting password");
        }
    });
}

// Smooth scroll for anchor links & contact form handling
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            alert('Thank you for your message! We will get back to you soon.');
            contactForm.reset();
        });
    }
});