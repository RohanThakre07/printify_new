import { useState } from "react";
import { api } from "@/App";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function UploadPage() {

  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setSelectedFile(file);

    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result);
    reader.readAsDataURL(file);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const res = await api.post("/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setAnalysis(res.data.analysis);
      toast.success("Image analyzed!");
    } catch (err) {
      toast.error("Analyze failed");
    }

    setLoading(false);
  };

  const handleCreateDraft = async () => {
    if (!selectedFile) return;

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const res = await api.post("/draft", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      toast.success("Draft created in Printify!");
    } catch (err) {
      toast.error("Draft creation failed");
    }

    setLoading(false);
  };

  return (
    <div className="space-y-4">

      <input type="file" accept="image/*" onChange={handleFileSelect} />

      {preview && (
        <img src={preview} className="w-48 rounded" />
      )}

      <Button onClick={handleAnalyze} disabled={!selectedFile || loading}>
        Analyze
      </Button>

      <Button onClick={handleCreateDraft} disabled={!selectedFile || loading}>
        Create Draft
      </Button>

    </div>
  );
}
