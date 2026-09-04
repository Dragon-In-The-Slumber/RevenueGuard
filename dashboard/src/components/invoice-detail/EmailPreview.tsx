export default function EmailPreview({ emailBody }: { emailBody: string }) {
  // Convert basic markdown and newlines
  const formattedBody = emailBody
    .replace(/\n/g, '<br/>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="text-blue-600 hover:underline">$1</a>')
    .replace(/{{payment_link}}/g, '<a href="#" class="text-blue-600 hover:underline">Razorpay Secure Payment Link</a>');

  return (
    <div className="bg-white rounded-md overflow-hidden text-black shadow-inner border border-white/20 mt-3">
      <div className="bg-gray-100 border-b border-gray-200 px-4 py-2 text-xs text-gray-500 font-sans flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-red-400"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-amber-400"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-green-400"></div>
        </div>
        <span>Message Preview</span>
      </div>
      <div className="p-4 text-sm font-sans text-gray-800 leading-relaxed" dangerouslySetInnerHTML={{ __html: formattedBody }} />
    </div>
  );
}
