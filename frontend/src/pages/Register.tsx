import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import qs from "qs";

const Register: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async () => {
    if (!username || !password) {
      alert("Please fill in all fields.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/register", { username, password });

      const response = await api.post(
        "/token",
        qs.stringify({ username, password }), // ใช้ qs เพื่อแปลงเป็น form-urlencoded
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      const response_login = await api.post(
        "/token",
        qs.stringify({ username, password }),
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      const token = response_login.data.access_token;
      localStorage.setItem("token", token);
      localStorage.setItem("token_type", response.data.token_type);

      await updateUser(token);
      navigate("/");
    } catch (error: any) {
      if (error.response && error.response.data) {
        alert(`Registration failed: ${error.response.data.detail}`);
      } else {
        alert("Registration failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const updateUser = async (token: string) => {
    try {
      await api.put(
        "/users/me",
        { visits: 1 }, // ส่งข้อมูลอัปเดต (เช่น เพิ่ม visit)
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
    } catch (error: any) {
      console.error("Failed to update user:", error.response?.data);
    }
  };
  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2 className="auth-title">Register</h2>
        <div className="form-group">
          <input
            type="text"
            className="form-input"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div className="form-group">
          <input
            type="password"
            className="form-input"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button
          className="auth-button"
          onClick={handleRegister}
          disabled={loading}
        >
          {loading ? "Processing..." : "Register"}
        </button>

        <p className="auth-redirect">
          Already have an account?{" "}
          <span
            className="auth-link"
            onClick={() => navigate("/login")}
          >
            Login
          </span>
        </p>
      </div>
    </div>
  );
};

export default Register;