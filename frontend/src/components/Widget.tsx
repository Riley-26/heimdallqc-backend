import React, { useEffect, useState } from 'react';
import { WidgetProps } from '../types';
import styles from '../styles/widget.module.css';
import { theme } from '../themes/mainTheme';
import { Logo } from './Logo';

import { Checkbox, FormGroup, FormControlLabel, ThemeProvider } from '@mui/material';
import { ArrowForwardIos, ArrowBackIos, MoreHoriz } from '@mui/icons-material';

export const HMDLWidget: React.FC<WidgetProps> = ({
    config,
    onClose,
    onOpen,
    onConfirm,
    onCheck,
    onSubmit,
    widgetState
}) => {

    // Theme class
    const themeClass = `${config.darkTheme && "dark"}`;

    return (
        <div className={`${styles.widgetContainer}`}>
            {/* Widget Collapsed */}
            {!widgetState.isOpen && (
                <ThemeProvider theme={theme}>
                    <div className={`${styles.widget}`}>
                        <div className={`${styles[themeClass] || ""} ${styles.widgetMain} ${styles.widgetMainColl}`}>
                            <div className={`${styles[themeClass] || ""} ${styles.widgetBody}`}>
                                <div style={{ display: "flex", alignItems: "center", marginRight: "12px" }}>
                                    <ArrowBackIos style={{ color: `#${ themeClass === "dark" ? "bbb" : "444" }`, cursor: "pointer", marginLeft: "12px" }} onClick={() => { onOpen?.() }} />
                                    <Logo colourMode={themeClass} />
                                </div>
                            </div>
                        </div>
                    </div>
                </ThemeProvider>
            )}

            {/* Widget Expanded */}
            {widgetState.isOpen && (
                <ThemeProvider theme={theme}>
                    <div className={`${styles.widget}`}>
                        <div className={`${styles[themeClass] || ""} ${styles.widgetMain}`}>
                            <div className={`${styles[themeClass] || ""} ${styles.widgetBody}`}>
                                <FormGroup>
                                    <div>
                                        <div className={`${styles[themeClass] || ""} ${styles.widgetForm}`}>
                                            <FormControlLabel sx={{ '& .MuiSvgIcon-root': { fontSize: 28 }, marginRight: "0" }} checked={widgetState.checked} control={<Checkbox sx={{ color: "text.primary" }} />} label="" onClick={() => { onCheck?.(!widgetState.checked) }} />
                                            <span>This contains AI generated content</span>
                                        </div>
                                        <button type='button' className={`${styles[themeClass] || ""} ${styles.widgetButton} ${widgetState.confirmed && styles.widgetButtonActive}`} onClick={() => {
                                            onConfirm?.(!widgetState.confirmed)
                                        }}>
                                            CONFIRM{widgetState.confirmed && "ED"}
                                        </button>
                                    </div>
                                </FormGroup>
                                <div style={{ display: "flex", alignItems: "center" }}>
                                    <ArrowForwardIos style={{ color: `#${ themeClass === "dark" ? "bbb" : "444" }`, cursor: "pointer" }} onClick={() => { onClose?.() }} />
                                    <Logo colourMode={themeClass} />
                                </div>
                            </div>
                        </div>
                    </div>
                </ThemeProvider>
            )}
        </div>
    );
};