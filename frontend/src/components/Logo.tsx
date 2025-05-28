import React, { useEffect, useState, memo } from 'react';
import styles from '../styles/widget.module.css';

export const Logo = memo(() => (
    <div className={`${styles.widgetLogoWrapper}`}>
        <img src="/Asset 4.svg" style={{ width: "80px" }} alt="Heimdall Logo" />
        <div style={{ display: "flex", flexDirection: "column", lineHeight: "1.1", marginTop: "8px" }}>
            <span className={`${styles.widgetLogoName}`} style={{ color: "#444", fontSize: "11px", fontWeight: "600" }}>
                MONITORED BY
            </span>
            <a href="#"><span className={`${styles.widgetLogoName}`}>HEIMDALL<sup>®</sup></span></a>
        </div>
    </div>
));