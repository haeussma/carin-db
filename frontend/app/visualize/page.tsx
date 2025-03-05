import { redirect } from "next/navigation";

export default function VisualizePage() {
    // Change the URL below to your desired destination
    redirect("http://localhost:7470/browser/");
    return null;
}
