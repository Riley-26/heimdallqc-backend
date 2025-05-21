import { useState } from 'react'
import { useHMDL } from "./hooks/useHMDL"
import './App.css'

function App() {
    const [text, setText] = useState("hello")

    const {
        WidgetComponent,
        widgetState,
        widgetActions,
        isLoading,
        error
    } = useHMDL({
        apiKey: "1"
    })

    return (
        <>
            <textarea></textarea>
            <WidgetComponent></WidgetComponent>
            <button onClick={() => {widgetActions.setText(text)}}>SUBMIT</button>
        </>
    )
}

export default App
