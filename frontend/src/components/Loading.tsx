import React, { useEffect, useState } from 'react';
import styles from '../styles/widget.module.css';

type LogoProps = {
    colourMode?: string;
}

export const Loading: React.FC<LogoProps> = ({ colourMode }) => {
    return (
        <div className={`${styles[colourMode || ""]} ${styles.widgetLoading}`}>
            <div className={`${styles[colourMode || ""]} ${styles.widgetSpinner}`}></div>
            <span>Analysing...</span>
        </div>
    );
};