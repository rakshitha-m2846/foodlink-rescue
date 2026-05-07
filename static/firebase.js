// ============================================================
// firebase.js – FoodLink Rescue
// Firebase App + Phone Auth initialization (Modular SDK v9)
// ============================================================
// This file is imported as an ES Module from login.html.
// It exports `auth` and a helper to set up the invisible reCAPTCHA verifier.
// ============================================================

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth, RecaptchaVerifier } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

// ----------------------------------------------------------
// Firebase project configuration
// ----------------------------------------------------------
const firebaseConfig = {
  apiKey:            "AIzaSyBWxNAPpcHG6AmWxunoI_4OeVZKX9HdXK0",
  authDomain:        "foodlink-rescue-94db1.firebaseapp.com",
  projectId:         "foodlink-rescue-94db1",
  storageBucket:     "foodlink-rescue-94db1.firebasestorage.app",
  messagingSenderId: "416612846128",
  appId:             "1:416612846128:web:e2f1f82b1e62473fac3bf5",
  measurementId:     "G-69CQL6P4HW",
};

// Initialize Firebase
const app  = initializeApp(firebaseConfig);
const auth = getAuth(app);

// ----------------------------------------------------------
// Invisible reCAPTCHA setup
// Must be called once, after the DOM element exists.
// buttonId – the ID of the "Send OTP" button element.
// ----------------------------------------------------------
function setupRecaptcha(buttonId) {
  if (window._recaptchaVerifier) {
    // Already initialized – reuse the existing verifier
    return window._recaptchaVerifier;
  }

  window._recaptchaVerifier = new RecaptchaVerifier(auth, buttonId, {
    size: "invisible",
    callback: () => {
      // reCAPTCHA solved – the OTP send flow will continue automatically
      console.log("[reCAPTCHA] Solved silently.");
    },
    "expired-callback": () => {
      console.warn("[reCAPTCHA] Token expired. Please try again.");
      window._recaptchaVerifier = null; // force re-init on next attempt
    },
  });

  return window._recaptchaVerifier;
}

export { auth, setupRecaptcha };
