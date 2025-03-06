"use client";

import SpreadsheetUploader from '@/components/spreadsheet-uploader';
import DataTableCard from '@/components/data-table';
import AskCard from '@/components/ask-card';

export default function Page() {
  return (
    <div className="min-h-screen bg-background text-foreground w-full">
      <div className="p-4 md:p-8 bg-card text-card-foreground space-y-8 w-full max-w-[1920px] mx-auto">
        {/* Add Data (Spreadsheet Upload) */}
        <section id="add-data" className="w-full">
          <SpreadsheetUploader />
        </section>

        {/* Search/Data Table */}
        <section id="search" className="w-full">
          <DataTableCard />
        </section>

        {/* Ask
        <section id="ask" className="w-full">
          <AskCard />
        </section> */}
      </div>
    </div>
  );
}
