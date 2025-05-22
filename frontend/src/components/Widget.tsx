import React from 'react';
import { WidgetProps } from '../types';
import styles from '../styles/widget.module.css';

export const HMDLWidget: React.FC<WidgetProps> = ({
    config,
    isOpen = false,
    onClose,
    onOpen,
    onSubmit
}) => {
    // Theme class
    const themeClass = `widget--${config.theme === 'auto'
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : (config.theme || 'light')}`;

    return (
        <div className={`${styles.widgetContainer}`}>
            {/* Widget Collapsed */}
            

            {/* Widget Expanded */}
            {isOpen && (
                <div className={`${styles.widget} ${themeClass}`}>
                    <div className={`${styles.widgetMain}`}>
                        <div className={`${styles.widgetHead}`}>
                            <h1 className={`${styles.widgetHeader}`}>HEIMDALL</h1>
                            
                        </div>
                        <div className={`${styles.widgetBody}`}>
                            <div className={`${styles.widgetImgWrapper}`}>
                                <img src="/Asset 3.svg" style={{ width:"80px" }}></img>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};