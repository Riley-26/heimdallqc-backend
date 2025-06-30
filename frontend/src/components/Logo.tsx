import React, { useEffect, useState, memo } from 'react';
import styles from '../styles/widget.module.css';

type LogoProps = {
    colourMode?: string;
}

export const Logo: React.FC<LogoProps> = ({ colourMode }) => {

    return (
        <div className={`${styles.widgetLogoWrapper}`}>
            <a href="http://localhost:3000" target='_blank'><img src="/Asset 7.svg" style={{ width: "60px", opacity: "80%", filter: `${ colourMode !== "dark" ? "invert(1) brightness(0.9)" : "" }` }} alt="Heimdall Logo" /></a>
            <div style={{ display: "flex", flexDirection: "column", lineHeight: "1.1", marginTop: "2px" }}>
                <h2 className={`${styles.widgetLogoName}`} style={{ color: `#${ colourMode === "dark" ? "aaa" : "444"}`, fontSize: "11px", fontWeight: "600" }}>
                    PROTECTED BY
                </h2>
                <h1 className={`${styles[colourMode || ""]} ${styles.widgetLogoName}`}>HEIMDALL<sup>®</sup></h1>
            </div>
            <div className={`${styles[colourMode || ""]} ${styles.widgetFooter}`}>
                <a href="http://localhost:3000/privacy" target='_blank'>Terms</a>
                <a href="http://localhost:3000/privacy" target='_blank'>Privacy</a>
            </div>
        </div>
    )
};