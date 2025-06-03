import React, { useEffect, useState, memo } from 'react';
import styles from '../styles/widget.module.css';

type LogoProps = {
    colourMode?: string;
}

export const Logo: React.FC<LogoProps> = ({ colourMode }) => {

    return (
        <div className={`${styles.widgetLogoWrapper}`}>
            <img src={colourMode === "dark" ? "/Asset 4.svg": "/Asset 4.svg"} style={{ width: "80px" }} alt="Heimdall Logo" />
            <div style={{ display: "flex", flexDirection: "column", lineHeight: "1.1", marginTop: "8px", marginBottom: "4px" }}>
                <span className={`${styles.widgetLogoName}`} style={{ color: `#${ colourMode === "dark" ? "aaa" : "444"}`, fontSize: "11px", fontWeight: "600" }}>
                    MONITORED BY
                </span>
                <a href="#"><span className={`${styles[colourMode || ""]} ${styles.widgetLogoName}`}>HEIMDALL<sup>®</sup></span></a>
            </div>
            <div className={`${styles[colourMode || ""]} ${styles.widgetFooter}`}>
                <a href="">Terms</a>
                <a href="">Privacy</a>
            </div>
        </div>
    )
};