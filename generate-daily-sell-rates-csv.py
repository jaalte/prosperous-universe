import prunpy as prun
import csv
import time



def main():
    sell_rates = {}
    for ticker in prun.loader.material_ticker_list:
        print(f"{ticker}: ", end="")
        history = prun.PriceHistory(ticker, 'NC1')
        print(f"{history.average_traded_daily:.2f} per day")
        sell_rates[ticker] = round(history.average_traded_daily, 2)

    # Get current date in iso format
    current_date = time.strftime("%Y-%m-%d")

    # Save sell_rates to csv file NC1_sell_rates.csv
    filename = f"NC1_sell_rates_{current_date}.csv"
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        for ticker, sell_rate in sell_rates.items():
            writer.writerow([ticker, sell_rate])
    print(f"File saved: {filename}")

if __name__ == '__main__':
    main()