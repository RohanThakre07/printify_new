import axios from "axios";
import UploadPage from "./pages/UploadPage";

export const api = axios.create({
  baseURL: "/api"
});

function App() {
  return (
    <div className="p-6">
      <UploadPage />
    </div>
  );
}

export default App;
