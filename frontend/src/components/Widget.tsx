import React, { useEffect, useState } from 'react';
import { WidgetProps } from '../types';
import styles from '../styles/widget.module.css';
import { Checkbox, FormGroup, FormControlLabel, ThemeProvider } from '@mui/material';
import { ArrowForwardIos, ArrowBackIos } from '@mui/icons-material';
import { theme } from '../themes/mainTheme';

export const HMDLWidget: React.FC<WidgetProps> = ({
    config,
    isOpen = false,
    onClose,
    onOpen,
    onConfirm,
    onSubmit
}) => {
    const [confirmed, setConfirmed] = useState(false)

    // Theme class
    const themeClass = `widget--${config.theme === 'auto'
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : (config.theme || 'light')}`;

    useEffect(() => {
        console.log("reset")
    }, [])

    return (
        <div className={`${styles.widgetContainer}`}>
            {/* Widget Collapsed */}
            {!isOpen && (
                <ThemeProvider theme={theme}>
                    <div className={`${styles.widget} ${themeClass}`}>
                        <div className={`${styles.widgetMain} ${styles.widgetMainColl}`}>
                            <div className={`${styles.widgetBody}`}>
                                <div>
                                    <ArrowBackIos style={{ color: "#222", cursor: "pointer", marginLeft: "8px" }} onClick={() => {onOpen?.()}}/>
                                </div>
                                <div className={`${styles.widgetLogoWrapper}`} style={{ margin: "0 12px 0 8px" }}>
                                    <img src="/Asset 4.svg" style={{ width:"80px" }}></img>
                                    <div style={{ display: "flex", flexDirection: "column", lineHeight: "1.1", marginTop: "8px" }}>
                                        <span className={`${styles.widgetLogoName}`} style={{ color: "#444", fontSize: "11px", fontWeight: "600" }}>MONITORED BY</span>
                                        <a href="#"><span className={`${styles.widgetLogoName}`}>HEIMDALL<sup>®</sup></span></a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </ThemeProvider>
            )}

            {/* Widget Expanded */}
            {isOpen && (
                <ThemeProvider theme={theme}>
                    <div className={`${styles.widget} ${themeClass}`}>
                        <div className={`${styles.widgetMain}`}>
                            <div className={`${styles.widgetBody}`}>
                                <FormGroup>
                                    <div>
                                        <div className={`${styles.widgetForm}`}>
                                            <FormControlLabel sx={{ '& .MuiSvgIcon-root': { fontSize: 28 }, marginRight: "0" }} control={<Checkbox sx={{ color: "text.primary" }}/>} label=""/>
                                            <span>This contains AI generated content</span>
                                        </div>
                                        <button type='button' className={`${styles.widgetButton} ${confirmed && styles.widgetButtonActive}`} onClick={() => {
                                            onConfirm?.(!confirmed)
                                            setConfirmed(!confirmed)
                                            }}>
                                            CONFIRM{ confirmed && "ED" }
                                        </button>
                                    </div>
                                </FormGroup>
                                <div className={`${styles.widgetLogo}`}>
                                    <div>
                                        <ArrowForwardIos style={{ color: "#222", cursor: "pointer" }} onClick={() => {onClose?.()}}/>
                                    </div>
                                    <div className={`${styles.widgetLogoWrapper}`}>
                                        <img src="/Asset 4.svg" style={{ width: "80px" }}></img>
                                        <div style={{ display: "flex", flexDirection: "column", lineHeight: "1.1", marginTop: "8px" }}>
                                            <span className={`${styles.widgetLogoName}`} style={{ color: "#444", fontSize: "11px", fontWeight: "600" }}>MONITORED BY</span>
                                            <a href="#"><span className={`${styles.widgetLogoName}`}>HEIMDALL<sup>®</sup></span></a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </ThemeProvider>
            )}
        </div>
    );
};