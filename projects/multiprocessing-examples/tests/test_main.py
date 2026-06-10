import main


def test_imap_preserves_order():
    args = [1, 2, 3, 4]
    result = main.run_imap_multiprocessing(
        func=main.func_single_argument, argument_list=args, num_processes=2
    )
    assert result == args
