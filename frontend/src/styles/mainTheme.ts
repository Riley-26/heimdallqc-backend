import { createTheme } from "@mui/material";
import { green, orange } from "@mui/material/colors";

export const theme = createTheme({
    palette: {
        primary: {
            main: "#222",
            dark: "#eeeeee",
            light: "#222222",
        },
        text: {
            primary: "#222",
            secondary: "#888888",
        }
    },
});