import React, { useState } from 'react';
import { WidgetProps } from '../types';
import styles from '../styles/widget.module.css';
import { Checkbox, FormGroup, FormControlLabel, ThemeProvider } from '@mui/material';
import { theme } from '../themes/mainTheme';

export const HMDLWidget: React.FC<WidgetProps> = ({
    config,
    isOpen = false,
    onClose,
    onOpen,
    onSubmit
}) => {
    const [confirmed, setConfirmed] = useState(false)

    // Theme class
    const themeClass = `widget--${config.theme === 'auto'
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : (config.theme || 'light')}`;

    return (
        <div className={`${styles.widgetContainer}`}>
            {/* Widget Collapsed */}
            

            {/* Widget Expanded */}
            {isOpen && (
                <ThemeProvider theme={theme}>
                    <div className={`${styles.widget} ${themeClass}`}>
                        <div className={`${styles.widgetMain}`}>
                            <div className={`${styles.widgetHead}`}>
                                <h1 className={`${styles.widgetHeader}`}>HEIMDALL</h1>
                                
                            </div>
                            <div className={`${styles.widgetBody}`}>
                                <FormGroup>
                                    <div>
                                        <div className={`${styles.widgetForm}`}>
                                            <FormControlLabel sx={{ '& .MuiSvgIcon-root': { fontSize: 32 }, marginRight: "0" }} control={<Checkbox sx={{ color: "text.primary" }}/>} label=""/>
                                            <span>This contains AI generated content</span>
                                        </div>
                                        <button className={`${styles.widgetButton} ${confirmed && styles.widgetButtonActive}`} onClick={() => {setConfirmed(!confirmed)}}>
                                            CONFIRM{ confirmed && "ED" }
                                        </button>
                                    </div>
                                </FormGroup>
                                <div className={`${styles.widgetImgWrapper}`}>
                                    <img src="/Asset 4.svg" style={{ width:"80px" }}></img>
                                </div>
                            </div>
                        </div>
                    </div>
                </ThemeProvider>
            )}
        </div>
    );
};