import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import qs from "qs";

const Login: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!username || !password) {
      alert("Please enter both username and password");
      return;
    }

    setLoading(true);
    try {
      // ทำการล็อกอิน
      const response = await api.post(
        "/token",
        qs.stringify({ username, password }),
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      const token = response.data.access_token;
      localStorage.setItem("token", token);
      localStorage.setItem("token_type", response.data.token_type);

      // อัปเดตข้อมูลผู้ใช้หลังจากล็อกอิน
      await updateUser(token);

      navigate("/");
    } catch (error: any) {
      console.error(error.response?.data);
      alert("Login failed. Please check your credentials.");
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
        <h2 className="auth-title">Login</h2>
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
          onClick={handleLogin}
          disabled={loading}
        >
          {loading ? "Processing..." : "Login"}
        </button>

        <p className="auth-redirect">
          Don't have an account?{" "}
          <span className="auth-link" onClick={() => navigate("/register")}>
            Register
          </span>
        </p>
      </div>
    </div>
  );
};

export default Login;
