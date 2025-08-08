import React from "react";
import styles from '../styles/widget.module.css';
import { InfoOutline } from '@mui/icons-material'
import Tooltip from '@mui/material/Tooltip'
import { styled } from '@mui/material/styles'
import { WatermarkProps } from "@/types";

const CustomTooltip = styled(
    ({ className, children, ...props }: React.ComponentProps<typeof Tooltip>) => (
        <Tooltip {...props} classes={{ popper: className }}>
            {children}
        </Tooltip>
    )
)`
    & .MuiTooltip-tooltip {
        background: radial-gradient(circle at center, rgba(32, 32, 32, 1) 0%, rgba(26, 26, 26, 1) 100%);
        color: #ffffff;
        padding: 12px 16px;
        border-radius: 6px;
        white-space: pre-wrap;
        box-shadow: 0 0 20px #00000022;
        min-width: 480px;
    }

    & .MuiTooltip-arrow {
        color: #1a1a1a;
        font-size: 24px;
    }
`;

export const WatermarkComponent: React.FC<WatermarkProps> = ({ items, size=70 }) => {

    return (
        <CustomTooltip title={
            <div style={{ padding: "12px 8px", position: "relative" }}>
                <a href="http://heimdallqc.com" target="_blank" style={{ position: "absolute", top: "0", right: "0", display: "flex", alignItems: "center" }}>
                    <img src="/Asset 8.svg" style={{ width: "30px", height: "30px" }} />
                    <h1 className={`${styles.watermarkLogoName}`} style={{ marginTop: "4px", marginLeft: "6px" }}>HEIMDALL®</h1>
                </a>
                <h1 className={`${styles.watermarkTitle}`}>Content Analysis</h1>
                {
                    items.citations && Object.keys(items.citations).length > 0 &&<div style={{ marginTop: "12px" }}>
                        {
                            Object.keys(items.citations).map((val, key) => {
                                return <div key={key} className={`${styles.watermarkCitation}`}>
                                    <p style={{ color: "#aaa" }}>[{`${val}`}]</p>
                                    <p>
                                        {`${items.citations?.[val]["link"]} - `}
                                        <a href={items.citations?.[val]["link"]} style={{ color: "#8BAFC7", textDecoration: "underline" }}>{`${items.citations?.[val]["title"]}`}</a>
                                    </p>
                                </div>
                            })
                        }
                    </div>
                }
                <div className={`${styles.watermarkAnalysis}`}>
                    <div style={{ marginTop: "16px", display: "flex", width: "100%", alignItems: "center", gap: "16px" }}>
                        <div style={{ height: "8px", width: "100%", maxWidth: "85%", borderRadius: "9999px", backgroundColor: "#27272a" }}>
                            <div
                                style={{
                                    width: `${items.aiResult}%`,
                                    height: "8px",
                                    borderRadius: "9999px",
                                    backgroundColor: "rgba(96, 165, 250, 0.5)"
                                }}
                            />
                        </div>
                        <span>{items.aiResult}%</span>
                    </div>
                    <div style={{ marginTop: "4px", display: "flex", width: "100%", alignItems: "center", gap: "16px" }}>
                        <div style={{ height: "8px", width: "100%", maxWidth: "85%", borderRadius: "9999px", backgroundColor: "#27272a" }}>
                            <div
                                style={{
                                    width: `${items.plagResult}%`,
                                    height: "8px",
                                    borderRadius: "9999px",
                                    backgroundColor: "rgba(22, 163, 74, 0.5)"
                                }}
                            />
                        </div>
                        <span>{items.plagResult}%</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "16px", marginTop: "12px" }}>
                        <span>
                            <strong>Key:</strong>
                        </span>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span
                                style={{
                                    display: "inline-block",
                                    borderRadius: "4px",
                                    backgroundColor: "rgba(96, 165, 250, 0.5)",
                                    padding: "0 8px",
                                    color: "#dbeafe",
                                    opacity: 0.8,
                                    fontWeight: "bold",
                                    width: "max-content"
                                }}
                            >
                                AI
                            </span>
                            <span
                                style={{
                                    display: "inline-block",
                                    borderRadius: "4px",
                                    backgroundColor: "rgba(22, 163, 74, 0.5)",
                                    padding: "0 8px",
                                    color: "#bbf7d0",
                                    opacity: 0.8,
                                    fontWeight: "bold",
                                    width: "max-content"
                                }}
                            >
                                Plagiarism
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        }
            arrow
            placement='top'
            
        >
            <div className={`${styles.watermark}`} style={{ width: `${size}px` }}>
                <img src="/Asset 8.svg" className={`${styles.watermarkImage}`} style={{ opacity: `${(items.plagResult >= 70 ? items.plagResult : items.aiResult)}%` }}/>
            </div>
        </CustomTooltip>
    )
}