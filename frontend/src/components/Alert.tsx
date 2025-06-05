import React, { useEffect, useState } from 'react';
import styles from '../styles/widget.module.css';
import { ArrowDropDown, Warning } from '@mui/icons-material';

type AlertProps = {
    colourMode?: string;
}

export const Alert: React.FC<AlertProps> = ({ colourMode }) => {
    return (
        <div className={`${styles[colourMode || ""]} ${styles.widgetAlert}`}>
            <Warning style={{ fontSize: "16px", color: `${colourMode === "dark" ? "#f59e0b" : "#a24a02"}` }} />
            <span>Please confirm that you have answered this correctly</span>
            <ArrowDropDown style={{ position: "absolute", bottom: "-17px", right: "47%", color: `${colourMode === "dark" ? "#454545cc" : "ddddddcc"}`, fontSize: "28px" }} />
        </div>
    );
};