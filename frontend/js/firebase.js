import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyA_suzf6TRILVBfFG2AQXlsPAeE865QJ60",
  authDomain: "agent-f3721.firebaseapp.com",
  projectId: "agent-f3721",
  storageBucket: "agent-f3721.firebasestorage.app",
  messagingSenderId: "643716556512",
  appId: "1:643716556512:web:6036805353595efde89285",
  measurementId: "G-461GRMTQ26"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

export { app, auth, db };
