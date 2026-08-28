export function ErrorState({ message }: { message: string }) {
  return <p className="text-sm text-red-400">{message}</p>;
}
