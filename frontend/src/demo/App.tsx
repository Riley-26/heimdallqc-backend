import { useEffect, useRef, useState, useMemo } from "react"
import { useHMDL } from "../hooks/useHMDL"
import "./App.css"

function App() {
    const textareaRef = useRef(null)
    const watermarkProps = {
        id: 1,
        plagResult: 40,
        aiResult: 65,
        citations: {
            "H0": {
                "title": "yeah",
                "link": "hello"
            },
            "H1": {
                "title": "yeah2",
                "link": "hello2"
            }
        }
    }

    const { HMDLWidget, widgetState, widgetActions, HMDLWatermark, isLoading, error } =
        useHMDL({
            apiKey: "vhzXGP2n4WahshqNIraKHa25UPpEvoarvZ3ogti2biInXjNj",
            darkTheme: true,
            initialOpen: true
        })

    // EVENT LISTENERS FOR ALL SUBMITS

    return (
        <>
            <div
                className=""
                style={{ display: "flex", flexDirection: "column" }}
            >
                <h1>HEIMDALL</h1>
                <textarea
                    ref={textareaRef}
                    style={{
                        width: "800px",
                        height: "300px",
                        fontSize: "18px",
                        resize: "vertical",
                        padding: "8px",
                        margin: "0 0 12px 0",
                    }}
                ></textarea>
            </div>
            <div>
                { HMDLWatermark(watermarkProps) }
            </div>
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                }}
            >
                { HMDLWidget() }
            </div>
            <button
                onClick={() => {
                    widgetActions.submit(`${textareaRef.current?.["value"]}`)
                }}
            >
                SUBMIT
            </button>
        </>
    )
}

export default App
