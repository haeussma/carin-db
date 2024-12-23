import SpreadsheetUploader from '@/components/spreadsheet-uploader';
import DataTableCard from '@/components/data-table';
import AskCard from '@/components/ask-card';

export default function Page() {
  return (
    <div className="space-y-8 p-8 bg-white">
      <SpreadsheetUploader />
      <DataTableCard />
      <AskCard />
    </div>
  );
}