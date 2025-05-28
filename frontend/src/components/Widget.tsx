import React, { useEffect, useState } from 'react';
import { WidgetProps } from '../types';
import styles from '../styles/widget.module.css';
import { theme } from '../themes/mainTheme';
import { Logo } from './Logo';

import { Checkbox, FormGroup, FormControlLabel, ThemeProvider } from '@mui/material';
import { ArrowForwardIos, ArrowBackIos } from '@mui/icons-material';

export const HMDLWidget: React.FC<WidgetProps> = ({
    config,
    isOpen = false,
    onClose,
    onOpen,
    onConfirm,
    confirmed,
    onCheck,
    checked,
    onSubmit
}) => {

    // Theme class
    const themeClass = `widget--${config.theme === 'auto'
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : (config.theme || 'light')}`;

    return (
        <div className={`${styles.widgetContainer}`}>
            {/* Widget Collapsed */}
            {!isOpen && (
                <ThemeProvider theme={theme}>
                    <div className={`${styles.widget} ${themeClass}`}>
                        <div className={`${styles.widgetMain} ${styles.widgetMainColl}`}>
                            <div className={`${styles.widgetBody}`}>
                                <div>
                                    <ArrowBackIos style={{ color: "#222", cursor: "pointer", marginLeft: "8px" }} onClick={() => { onOpen?.() }} />
                                </div>
                                <div style={{ margin: "0 12px 0 8px" }}>
                                    <Logo />
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
                                            <FormControlLabel sx={{ '& .MuiSvgIcon-root': { fontSize: 28 }, marginRight: "0" }} checked={checked} control={<Checkbox sx={{ color: "text.primary" }} />} label="" onClick={() => { onCheck?.(!checked) }} />
                                            <span>This contains AI generated content</span>
                                        </div>
                                        <button type='button' className={`${styles.widgetButton} ${confirmed && styles.widgetButtonActive}`} onClick={() => {
                                            onConfirm?.(!confirmed)
                                        }}>
                                            CONFIRM{confirmed && "ED"}
                                        </button>
                                    </div>
                                </FormGroup>
                                <div className={`${styles.widgetLogo}`}>
                                    <div>
                                        <ArrowForwardIos style={{ color: "#222", cursor: "pointer" }} onClick={() => { onClose?.() }} />
                                    </div>
                                    <Logo />
                                </div>
                            </div>
                        </div>
                    </div>
                </ThemeProvider>
            )}
        </div>
    );
};