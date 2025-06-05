import { useEffect, useRef, useState, useMemo } from 'react'
import { useHMDL } from "../hooks/useHMDL"
import './App.css'

function App() {
    const textareaRef = useRef(null)

    const {
        WidgetComponent,
        widgetState,
        widgetActions,
        isLoading,
        error
    } = useHMDL({
        apiKey: "SkdsJXjnDfdctDSGJwBpPnBW6peOvb34oMbyQxcQfPfeDVTI",
        darkTheme: true,
        initialOpen: true
    })

    return (
        <>
            <div className='' style={{ display: "flex", flexDirection: "column" }}>
                <h1>HEIMDALL</h1>
                <textarea ref={textareaRef} style={{ width: "800px", height: "300px", fontSize: "18px", resize: "vertical", padding: "8px", margin: "0 0 12px 0" }}></textarea>
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                {WidgetComponent()}
            </div>
            <button onClick={() => { widgetActions.submit(`${textareaRef.current?.["value"]}`) }}>SUBMIT</button>
        </>
    )
}

export default App
