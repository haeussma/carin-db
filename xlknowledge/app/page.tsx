import SpreadsheetUploader from '@/components/spreadsheet-uploader';
import AskCard from '@/components/ask-card';

export default function Page() {
  return (
    <div className="space-y-8 p-8">
      <SpreadsheetUploader />
      <AskCard />
    </div>
  );
}