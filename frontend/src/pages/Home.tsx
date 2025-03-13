import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";

const Home: React.FC = () => {
    const navigate = useNavigate();
    const [imageUrl, setImageUrl] = useState("");
    const [loading, setLoading] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false); // ตรวจสอบว่า login หรือไม่

    const fetchRandomImage = async () => {
        setLoading(true);
        try {
            const response = "https://random-image-pepebigotes.vercel.app/api/random-image";
            setImageUrl(response);

        } catch (error) {
            console.error("Failed to fetch image:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const token = localStorage.getItem("token");
        console.log(token)
        console.log(!token)
        
        if (!token) {
          navigate("/login");
        } else {
          setIsAuthenticated(true); // ยืนยันว่า token มีอยู่
          fetchRandomImage();
        }
      }, []);

    if (!isAuthenticated) {
        return null; // ป้องกันการ render ก่อนตรวจสอบเสร็จ
      }
    
      return (
        <div className="page-container">
          <Navbar />
          <div className="content-container">
            <h2 className="page-title">Premium Random Gallery</h2>
            <div className="image-container">
              {loading ? (
                <div className="loader"></div>
              ) : (
                <img
                  src={imageUrl}
                  alt="Random Premium Content"
                  className="gallery-image"
                />
              )}
            </div>
            <button className="premium-button" onClick={() => window.location.reload()}>
              Generate New Image
            </button>
          </div>
        </div>
      );
    };

export default Home;
